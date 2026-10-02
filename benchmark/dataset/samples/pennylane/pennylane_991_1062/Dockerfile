FROM benchmark-base:pennylane_991_1062

ENV SAMPLE_ID=pennylane_991_1062
ENV REPOSITORY_URL=https://github.com/PennyLaneAI/pennylane.git
ENV BASE_COMMIT=2c9f3c83305a6a541a65adbcfcf3fdf0514d75a8
ENV PATCHED_COMMIT=a7bf5c9ec7db785bd80a6d52a08c0de475382f0d
ENV FAIL_PASS_TEST_PATHS="tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward_broadcasting[True-2-2-n_qubits0-output_dim0-torch] tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward_broadcasting[True-5-4-n_qubits1-output_dim1-torch]"
ENV PASS_PASS_TEST_PATHS="tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward_single_input[True-n_qubits0-output_dim0-torch] tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward_single_input[True-n_qubits1-output_dim1-torch] tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward[True-n_qubits0-output_dim0-torch] tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward[True-n_qubits1-output_dim1-torch]"

WORKDIR /benchmark
COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
