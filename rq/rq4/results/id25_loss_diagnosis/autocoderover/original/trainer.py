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

"""Quantum Kernel Trainer."""

from copy import deepcopy
from typing import Optional

import numpy as np
from qiskit.algorithms.optimizers import Optimizer, SPSA

from qiskit_machine_learning.kernels import QuantumKernel
from qiskit_machine_learning.utils.loss_functions.kernel_loss_functions import (
    KernelLoss,
    SVCLoss,
)


class QuantumKernelTrainerResult:
    """Result object for QuantumKernelTrainer."""

    def __init__(self):
        self._optimizer_result = None
        self._optimized_kernel = None

    @property
    def optimizer_result(self):
        """Returns the optimizer result."""
        return self._optimizer_result

    @optimizer_result.setter
    def optimizer_result(self, value):
        """Sets the optimizer result."""
        self._optimizer_result = value

    @property
    def quantum_kernel(self):
        """Returns the optimized quantum kernel."""
        return self._optimized_kernel

    @quantum_kernel.setter
    def quantum_kernel(self, value):
        """Sets the optimized quantum kernel."""
        self._optimized_kernel = value


class QuantumKernelTrainer:
    """Trainer for optimizing the user parameters of a QuantumKernel."""

    def __init__(
        self,
        quantum_kernel: QuantumKernel,
        loss: Optional[KernelLoss] = None,
        optimizer: Optional[Optimizer] = None,
        initial_point: Optional[np.ndarray] = None,
    ):
        """Creates a new QuantumKernelTrainer instance.

        Args:
            quantum_kernel: the quantum kernel to optimize.
            loss: the kernel loss function to use. Defaults to SVCLoss().
            optimizer: the optimizer to use. Defaults to SPSA().
            initial_point: the initial point for the optimization.

        Raises:
            ValueError: if the quantum kernel does not have trainable user parameters.
        """
        if not quantum_kernel.user_parameters:
            raise ValueError(
                "The quantum kernel must have trainable user parameters."
            )

        self._quantum_kernel = quantum_kernel
        self._loss = loss if loss is not None else SVCLoss()
        self._optimizer = optimizer if optimizer is not None else SPSA()
        self._initial_point = initial_point

    def fit(self, data, labels) -> QuantumKernelTrainerResult:
        """Fits the trainer on labeled data.

        Args:
            data: the training data.
            labels: the training labels.

        Returns:
            A QuantumKernelTrainerResult containing the optimization results and
            an optimized quantum kernel.
        """
        initial_point = self._initial_point
        if initial_point is None:
            initial_point = np.random.rand(len(self._quantum_kernel.user_parameters))

        def objective(parameter_values):
            return self._loss.evaluate(
                parameter_values, self._quantum_kernel, data, labels
            )

        optimizer_result = self._optimizer.minimize(
            fun=objective, x0=initial_point
        )

        # Create a copy of the original kernel and assign the optimized parameters
        optimized_kernel = deepcopy(self._quantum_kernel)
        optimized_kernel.assign_user_parameters(optimizer_result.x)

        result = QuantumKernelTrainerResult()
        result.optimizer_result = optimizer_result
        result.quantum_kernel = optimized_kernel

        return result
