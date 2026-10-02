FROM benchmark-base:qiskit_nature_129_341

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_129_341
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/129
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/341
ENV BASE_COMMIT=a06f378a219d650d96e16db96d763ea4aec9cfc2
ENV PATCHED_COMMIT=357fe78db796414292a51bd720e813cf57cbc170
ENV PR_HEAD_COMMIT=357fe78db796414292a51bd720e813cf57cbc170
ENV FAIL_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_to_matrix"
ENV PASS_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_add test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_matmul_multi test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_reduce test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_hermiticity"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
