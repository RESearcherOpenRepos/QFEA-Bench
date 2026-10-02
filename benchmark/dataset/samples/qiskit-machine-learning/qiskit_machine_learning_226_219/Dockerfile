ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_226_219
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_226_219
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/226
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/219
ENV BASE_COMMIT=3cfecd6fd149920962e77dceaeaafcf233da9cf7
ENV PATCHED_COMMIT=0f2d1e8fc0c20376f9c7dcc7e68b0840f6cd511b
ENV PR_HEAD_COMMIT=0f2d1e8fc0c20376f9c7dcc7e68b0840f6cd511b
ENV FAIL_PASS_TEST_PATHS="test/kernels/test_qkernel.py::TestQuantumKernelFreeParameters::test_user_parameters"
ENV PASS_PASS_TEST_PATHS="test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_innerproduct test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_selfinnerproduct test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_statevector"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
