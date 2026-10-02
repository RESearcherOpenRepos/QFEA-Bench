FROM benchmark-base:pennylane_166_588

ENV SAMPLE_ID=pennylane_166_588
ENV REPOSITORY_URL=https://github.com/PennyLaneAI/pennylane.git
ENV BASE_COMMIT=606e2b0b1b038f1e193a1dd83c282d36c3c95739
ENV PATCHED_COMMIT=d5986483da271a6de0a319c1b4e17c2f73d11402
ENV FAIL_PASS_TEST_PATHS="tests/qnn/test_qnn_torch.py::TestTorchLayer::test_forward[n_qubits0-output_dim0-torch] tests/qnn/test_qnn_torch.py::TestTorchLayer::test_gradients[n_qubits0-output_dim0-torch] tests/qnn/test_qnn_torch.py::TestTorchLayerIntegration::test_module_gradients[n_qubits0-output_dim0-torch]"
ENV PASS_PASS_TEST_PATHS=""

WORKDIR /benchmark
COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
