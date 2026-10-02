FROM benchmark-base:qiskit_nature_3_25

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_3_25
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/3
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/25
ENV BASE_COMMIT=34d460f06c9bad858aa413f2821becb2c5b33752
ENV PATCHED_COMMIT=e8e7b736e0dad78206af87ed4c524933a5e5292a
ENV PR_HEAD_COMMIT=e8e7b736e0dad78206af87ed4c524933a5e5292a
ENV FAIL_PASS_TEST_PATHS="test/operators/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/test_fermionic_op.py::TestFermionicOp::test_init_invalid test/operators/test_fermionic_op.py::TestFermionicOp::test_mul test/operators/test_fermionic_op.py::TestFermionicOp::test_add test/operators/test_fermionic_op.py::TestFermionicOp::test_matmul_multi test/operators/test_fermionic_op.py::TestFermionicOp::test_reduce"
ENV PASS_PASS_TEST_PATHS="test/test_fermionic_operator.py::TestFermionicOperator::test_transform test/test_fermionic_operator.py::TestFermionicOperator::test_freezing_core test/test_fermionic_operator.py::TestFermionicOperator::test_bksf_mapping test/test_fermionic_transformation.py::TestFermionicTransformation::test_jordan_wigner test/test_fermionic_transformation.py::TestFermionicTransformation::test_parity"
ENV FAIL_PASS_EXTRA_FILES="test/operators/test_fermionic_op.py"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
