ARG BASE_IMAGE=benchmark-base:qiskit_machine_learning_227_244
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_machine_learning_227_244
ENV REPOSITORY=qiskit-community/qiskit-machine-learning
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-machine-learning.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-machine-learning/issues/227
ENV PR_URL=https://github.com/qiskit-community/qiskit-machine-learning/pull/244
ENV BASE_COMMIT=26bf303b4a7897ac3f0934d630d236660afa4b98
ENV PATCHED_COMMIT=93f8cbb3f4f92d40648d616312a4201dedf71113
ENV PR_HEAD_COMMIT=93f8cbb3f4f92d40648d616312a4201dedf71113
ENV FAIL_PASS_TEST_PATHS="test/kernels/algorithms/test_qkernel_trainer.py::TestQuantumKernelTrainer::test_qkt"
ENV PASS_PASS_TEST_PATHS="test/kernels/test_qkernel.py::TestQuantumKernelClassify::test_callable test/kernels/test_qkernel.py::TestQuantumKernelClassify::test_precomputed test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_no_backend test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_qasm_nopsd test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_qasm_psd test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_qasm_symmetric test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_qasm_unsymmetric test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_sv_symmetric test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_sv_unsymmetric test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_x_more_dim test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_x_one_dim test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_xy_one_dim test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_y_feature_dim test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_y_more_dim test/kernels/test_qkernel.py::TestQuantumKernelEvaluate::test_y_one_dim test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_innerproduct test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_innerproduct_nomeasurement test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_selfinnerprodect_nomeasurement test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_selfinnerproduct test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_statevector test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_xdim test/kernels/test_qkernel.py::TestQuantumKernelConstructCircuit::test_ydim"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
