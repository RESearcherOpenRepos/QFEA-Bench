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

""" Kernel Loss utilities """

from abc import ABC, abstractmethod

import numpy as np
from sklearn.svm import SVC


class KernelLoss(ABC):
    """
    Abstract base class for computing the loss of a kernel function.
    """

    def __call__(
        self,
        parameter_values: np.ndarray,
        quantum_kernel,
        data: np.ndarray,
        labels: np.ndarray,
    ) -> float:
        """
        This method calls the ``evaluate`` method. This is a convenient method to compute
        the kernel loss.
        """
        return self.evaluate(parameter_values, quantum_kernel, data, labels)

    @abstractmethod
    def evaluate(
        self,
        parameter_values: np.ndarray,
        quantum_kernel,
        data: np.ndarray,
        labels: np.ndarray,
    ) -> float:
        """
        An abstract method for evaluating the loss function. Inputs are expected in a shape
        of ``(N, *)``. Where ``N`` is a number of samples. Loss is computed for each sample
        individually.

        Args:
            parameter_values: an array of values to assign to the user parameters in the
                ``quantum_kernel``.
            quantum_kernel: a ``QuantumKernel`` (or compatible) object to evaluate.
            data: an array of the training data.
            labels: an array of the training labels.

        Returns:
            The loss value.
        """
        raise NotImplementedError


class SVCLoss(KernelLoss):
    r"""
    This class provides a support vector classification (SVC) loss function for kernel
    training. The loss is defined as the classification error of a support vector classifier
    fit on the kernel matrix evaluated at the given parameter values:

    .. math::

        \text{SVCLoss}(\boldsymbol{\theta}) = 1 - \text{accuracy}_{\text{SVC}}(K(\boldsymbol{\theta})).

    The SVC is fit using a precomputed kernel matrix, and any keyword arguments supplied to
    the constructor are forwarded to :class:`sklearn.svm.SVC`.
    """

    def __init__(self, **kwargs) -> None:
        """
        Args:
            **kwargs: Arbitrary keyword arguments to pass to ``sklearn.svm.SVC``. The
                ``kernel`` keyword is always set to ``"precomputed"`` and may not be
                overridden.
        """
        self._kwargs = kwargs

    def evaluate(
        self,
        parameter_values: np.ndarray,
        quantum_kernel,
        data: np.ndarray,
        labels: np.ndarray,
    ) -> float:
        # Assign the user parameters to the kernel. The trainer is responsible for
        # passing a copy of the kernel so that the original is not mutated.
        quantum_kernel.assign_user_parameters(parameter_values)

        # Evaluate the kernel matrix on the training data.
        kernel_matrix = quantum_kernel.evaluate(data)

        # Fit an SVC with a precomputed kernel matrix, forwarding any user kwargs.
        kwargs = dict(self._kwargs)
        kwargs["kernel"] = "precomputed"
        svc = SVC(**kwargs)
        svc.fit(kernel_matrix, labels)

        # The loss is the classification error (1 - accuracy).
        loss = 1.0 - svc.score(kernel_matrix, labels)

        return float(loss)
