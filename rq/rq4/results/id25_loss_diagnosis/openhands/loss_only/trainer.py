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

""" Quantum Kernel Trainer """

from typing import Optional, Sequence

import copy
import numpy as np
from qiskit.algorithms.optimizers import Optimizer, SPSA
from qiskit.algorithms.optimizers.optimizer import OptimizerResult

from ...exceptions import QiskitMachineLearningError
from ...utils.loss_functions import KernelLoss, SVCLoss
from ..quantum_kernel import QuantumKernel


class QuantumKernelTrainerResult:
    """Contains the results of a ``QuantumKernelTrainer``."""

    def __init__(self) -> None:
        self._optimal_parameters: Optional[np.ndarray] = None
        self._optimal_value: Optional[float] = None
        self._optimizer_evals: Optional[int] = None
        self._optimizer_time: Optional[float] = None
        self._quantum_kernel: Optional[QuantumKernel] = None

    @property
    def optimal_parameters(self) -> Optional[np.ndarray]:
        """Returns the optimal user parameters found by the optimizer."""
        return self._optimal_parameters

    @optimal_parameters.setter
    def optimal_parameters(self, value: np.ndarray) -> None:
        """Sets the optimal user parameters found by the optimizer."""
        self._optimal_parameters = value

    @property
    def optimal_value(self) -> Optional[float]:
        """Returns the optimal value of the kernel loss found by the optimizer."""
        return self._optimal_value

    @optimal_value.setter
    def optimal_value(self, value: float) -> None:
        """Sets the optimal value of the kernel loss found by the optimizer."""
        self._optimal_value = value

    @property
    def optimizer_evals(self) -> Optional[int]:
        """Returns the number of optimizer evaluations."""
        return self._optimizer_evals

    @optimizer_evals.setter
    def optimizer_evals(self, value: int) -> None:
        """Sets the number of optimizer evaluations."""
        self._optimizer_evals = value

    @property
    def optimizer_time(self) -> Optional[float]:
        """Returns the time taken by the optimizer, if available."""
        return self._optimizer_time

    @optimizer_time.setter
    def optimizer_time(self, value: float) -> None:
        """Sets the time taken by the optimizer."""
        self._optimizer_time = value

    @property
    def quantum_kernel(self) -> Optional[QuantumKernel]:
        """Returns the optimized quantum kernel."""
        return self._quantum_kernel

    @quantum_kernel.setter
    def quantum_kernel(self, value: QuantumKernel) -> None:
        """Sets the optimized quantum kernel."""
        self._quantum_kernel = value


class QuantumKernelTrainer:
    """
    Quantum Kernel Trainer.

    This class provides a trainer for optimizing the user parameters of a
    :class:`~qiskit_machine_learning.kernels.QuantumKernel` against labeled training data
    using a kernel-specific loss function and an optimizer.
    """

    def __init__(
        self,
        quantum_kernel: QuantumKernel,
        loss: Optional[KernelLoss] = None,
        optimizer: Optional[Optimizer] = None,
        initial_point: Optional[Sequence[float]] = None,
    ) -> None:
        """
        Args:
            quantum_kernel: A ``QuantumKernel`` whose user parameters are to be optimized.
                The kernel must expose trainable user parameters.
            loss: A kernel loss function implementing the ``KernelLoss`` interface. If ``None``
                defaults to :class:`~qiskit_machine_learning.utils.loss_functions.SVCLoss`.
            optimizer: An instance of an optimizer to be used in training. If ``None`` defaults
                to :class:`~qiskit.algorithms.optimizers.SPSA`.
            initial_point: Initial point for the optimizer to start from. If ``None`` defaults
                to an array of zeros with one entry per user parameter.

        Raises:
            QiskitMachineLearningError: If the quantum kernel does not expose trainable user
                parameters.
        """
        if quantum_kernel.user_parameters is None:
            raise QiskitMachineLearningError(
                "The quantum kernel must expose trainable user parameters to be trained."
            )

        self._quantum_kernel = quantum_kernel
        self._loss = loss if loss is not None else SVCLoss()
        self._optimizer = optimizer if optimizer is not None else SPSA()
        self._initial_point = initial_point

    @property
    def quantum_kernel(self) -> QuantumKernel:
        """Returns the quantum kernel being trained."""
        return self._quantum_kernel

    @property
    def loss(self) -> KernelLoss:
        """Returns the kernel loss function used in training."""
        return self._loss

    @property
    def optimizer(self) -> Optimizer:
        """Returns the optimizer used in training."""
        return self._optimizer

    @property
    def initial_point(self) -> Optional[Sequence[float]]:
        """Returns the initial point used in training."""
        return self._initial_point

    def fit(self, data: np.ndarray, labels: np.ndarray) -> QuantumKernelTrainerResult:
        """
        Fit the quantum kernel trainer on labeled data.

        The user parameters of the input quantum kernel are optimized against the provided
        data and labels. The input quantum kernel is not mutated; the returned result
        carries an optimized copy of the kernel.

        Args:
            data: The training data.
            labels: The training labels.

        Returns:
            A ``QuantumKernelTrainerResult`` containing the optimizer metadata and the
            optimized quantum kernel.

        Raises:
            QiskitMachineLearningError: If the quantum kernel does not expose trainable user
                parameters.
        """
        # Reject quantum kernels that do not expose trainable user parameters.
        if self._quantum_kernel.user_parameters is None:
            raise QiskitMachineLearningError(
                "The quantum kernel must expose trainable user parameters to be trained."
            )

        num_parameters = len(self._quantum_kernel.user_parameters)

        # Determine the initial point for the optimizer.
        if self._initial_point is None:
            initial_point = np.zeros(num_parameters)
        else:
            initial_point = np.array(self._initial_point, dtype=float)

        # Work on a copy so the input quantum kernel is not mutated by training.
        quantum_kernel = copy.deepcopy(self._quantum_kernel)

        # Define the objective function for the optimizer.
        def objective(parameter_values: np.ndarray) -> float:
            return self._loss.evaluate(parameter_values, quantum_kernel, data, labels)

        # Run the optimizer.
        opt_result: OptimizerResult = self._optimizer.minimize(objective, initial_point)

        # Assign the optimal parameters to the kernel copy.
        quantum_kernel.assign_user_parameters(opt_result.x)

        # Build and return the result.
        result = QuantumKernelTrainerResult()
        result.optimal_parameters = opt_result.x
        result.optimal_value = opt_result.fun
        result.optimizer_evals = opt_result.nfev
        result.optimizer_time = getattr(opt_result, "optimizer_time", None)
        result.quantum_kernel = quantum_kernel

        return result
