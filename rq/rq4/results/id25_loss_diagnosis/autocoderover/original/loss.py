# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Kernel Loss Functions."""

from abc import ABC, abstractmethod

import numpy as np
from sklearn.svm import SVC


class KernelLoss(ABC):
    """An abstract class for kernel loss functions."""

    @abstractmethod
    def evaluate(self, parameter_values, quantum_kernel, data, labels):
        """Evaluates the kernel loss.

        Args:
            parameter_values: the parameter values to be used by the quantum kernel.
            quantum_kernel: the quantum kernel to evaluate.
            data: the training data.
            labels: the training labels.

        Returns:
            The loss value.
        """
        raise NotImplementedError


class SVCLoss(KernelLoss):
    """A kernel loss based on the support vector classifier."""

    def __init__(self, **kwargs):
        """Creates a new SVCLoss instance.

        Args:
            **kwargs: keyword arguments to be passed to sklearn.svm.SVC.
        """
        self._svc_kwargs = kwargs

    def evaluate(self, parameter_values, quantum_kernel, data, labels):
        """Evaluates the SVC-based kernel loss.

        Args:
            parameter_values: the parameter values to be used by the quantum kernel.
            quantum_kernel: the quantum kernel to evaluate.
            data: the training data.
            labels: the training labels.

        Returns:
            The loss value.
        """
        quantum_kernel.assign_user_parameters(parameter_values)
        kernel_matrix = quantum_kernel.evaluate(data)
        svc = SVC(kernel="precomputed", **self._svc_kwargs)
        svc.fit(kernel_matrix, labels)
        return 1.0 - svc.score(kernel_matrix, labels)
