FROM benchmark-base:qiskit_nature_22_35

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_22_35
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/22
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/35
ENV BASE_COMMIT=c6f14c92a6fc289957ba7dc42ced8feef89413f7
ENV PATCHED_COMMIT=88ad9f95907377296a0cd9f9d3da63379fa867f2
ENV PR_HEAD_COMMIT=88ad9f95907377296a0cd9f9d3da63379fa867f2
ENV FAIL_PASS_TEST_PATHS="test/operators/test_spin_op.py::TestSpinOp::test_init_label_2_X test/operators/test_spin_op.py::TestSpinOp::test_init_dense_label_11_XY test/operators/test_spin_op.py::TestSpinOp::test_init_pm_label test/operators/test_spin_op.py::TestSpinOp::test_to_matrix_two_qutrit_07_XY test/operators/test_spin_op.py::TestSpinOp::test_consistency_with_pauli_48_XYZ"
ENV PASS_PASS_TEST_PATHS="test/operators/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/test_fermionic_op.py::TestFermionicOp::test_add test/operators/test_fermionic_op.py::TestFermionicOp::test_matmul_multi test/operators/test_fermionic_op.py::TestFermionicOp::test_pow test/operators/test_fermionic_op.py::TestFermionicOp::test_adjoint test/operators/test_fermionic_op.py::TestFermionicOp::test_reduce"
ENV FAIL_PASS_EXTRA_FILES="test/operators/test_spin_op.py"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
