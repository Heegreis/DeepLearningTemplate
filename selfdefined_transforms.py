#import
import torch.nn as nn
import torch.nn.functional as F
from torchaudio.functional import lowpass_biquad, highpass_biquad
import numpy as np
from typing import Any
import torch
import torchvision


#class
class DigitalFilter(nn.Module):
    def __init__(self, filter_type, sample_rate, cutoff_freq) -> None:
        super().__init__()
        assert filter_type in [
            'bandpass', 'lowpass', 'highpass', None
        ], 'please check the filter_type argument.\nfilter_type: {}\nvalid: {}'.format(
            filter_type, ['bandpass', 'lowpass', 'highpass', None])
        if type(cutoff_freq) != list:
            cutoff_freq = [cutoff_freq]
        cutoff_freq = np.array(cutoff_freq)
        # check if the cutoff frequency satisfied Nyquist theorem
        assert not any(
            cutoff_freq / (sample_rate * 0.5) > 1
        ), 'please check the cutoff_freq argument.\ncutoff_freq: {}\nvalid: {}'.format(
            cutoff_freq, [1, sample_rate // 2])
        self.filter_type = filter_type
        self.sample_rate = sample_rate
        self.cutoff_freq = cutoff_freq

    def __call__(self, waveform):
        if self.filter_type is None or self.filter_type == 'None':
            return waveform
        elif self.filter_type == 'bandpass':
            waveform = lowpass_biquad(waveform=waveform,
                                      sample_rate=self.sample_rate,
                                      cutoff_freq=max(self.cutoff_freq))
            waveform = highpass_biquad(waveform=waveform,
                                       sample_rate=self.sample_rate,
                                       cutoff_freq=min(self.cutoff_freq))
        elif self.filter_type == 'lowpass':
            waveform = lowpass_biquad(waveform=waveform,
                                      sample_rate=self.sample_rate,
                                      cutoff_freq=max(self.cutoff_freq))
        elif self.filter_type == 'highpass':
            waveform = highpass_biquad(waveform=waveform,
                                       sample_rate=self.sample_rate,
                                       cutoff_freq=min(self.cutoff_freq))
        return waveform


class PadWaveform(nn.Module):
    def __init__(self, max_waveform_length) -> None:
        super().__init__()
        self.max_waveform_length = max_waveform_length

    def forward(self, waveform):
        # the dimension of waveform is (channels, length)
        channels, length = waveform.shape
        diff = self.max_waveform_length - length
        if diff >= 0:
            pad = (int(np.ceil(diff / 2)), int(np.floor(diff / 2)))
            waveform = F.pad(input=waveform, pad=pad)
        else:
            waveform = waveform[:, :self.max_waveform_length]
        return waveform


class OneHotEncoder:
    def __init__(self, num_classes) -> None:
        self.num_classes = num_classes

    def __call__(self, target) -> Any:
        #target dimention should be (num_classes,) or a scaler
        if type(target) != int and len(target) == self.num_classes:
            return target
        else:
            if type(target) == torch.Tensor:
                # this is only for mask image in the segmentation task
                target = torch.eye(self.num_classes)[
                    target]  #the target dimension is (1, w, h, num_classes)
                return target[0].permute(
                    2, 0, 1)  #the target dimension is (num_classes, w, h)
            else:
                return np.eye(self.num_classes)[target]


class LabelSmoothing(OneHotEncoder):
    def __init__(self, alpha, num_classes) -> None:
        super().__init__(num_classes=num_classes)
        self.alpha = alpha

    def __call__(self, target) -> Any:
        target = super().__call__(target)
        return (1 - self.alpha) * target + (self.alpha / self.num_classes)


class ResizePadding(nn.Module):
    def __init__(self,
                 target_size: int,
                 interpolation=torchvision.transforms.functional.
                 InterpolationMode.BILINEAR,
                 max_size=None,
                 antialias=None) -> None:
        super().__init__()
        self.target_size = target_size
        self.interpolation = interpolation
        self.max_size = max_size
        self.antialias = antialias

    def forward(self, img):
        w, h = img.size  #img is PIL image
        ratio = min(self.target_size / w, self.target_size / h)
        target_w, target_h = int(w * ratio), int(h * ratio)
        img = torchvision.transforms.functional.resize(
            img=img,
            size=(target_h, target_w),
            interpolation=self.interpolation,
            max_size=self.max_size,
            antialias=self.antialias)
        img = torchvision.transforms.functional.to_tensor(
            img)  #convert PIL image to tensor
        diff_w = self.target_size - target_w
        diff_h = self.target_size - target_h
        pad = (int(np.ceil(diff_w / 2)), int(np.floor(diff_w / 2)),
               int(np.ceil(diff_h / 2)), int(np.floor(diff_h / 2)))
        img = F.pad(input=img, pad=pad)
        return torchvision.transforms.functional.to_pil_image(
            pic=img, mode=None)  #convert tensor to PIL image


class PaddingResize(torchvision.transforms.Resize):
    def __init__(self,
                 size,
                 interpolation=torchvision.transforms.functional.
                 InterpolationMode.BILINEAR,
                 max_size=None,
                 antialias=None):
        super().__init__(size, interpolation, max_size, antialias)

    def forward(self, img):
        w, h = img.size  #img is PIL image
        img = torchvision.transforms.functional.to_tensor(
            img)  #convert PIL image to tensor
        target_size = max(w, h)
        diff_w = target_size - w
        diff_h = target_size - h
        pad = (int(np.ceil(diff_w / 2)), int(np.floor(diff_w / 2)),
               int(np.ceil(diff_h / 2)), int(np.floor(diff_h / 2)))
        img = F.pad(input=img, pad=pad)
        img = torchvision.transforms.functional.to_pil_image(
            pic=img, mode=None)  #convert tensor to PIL image
        return super().forward(img=img)