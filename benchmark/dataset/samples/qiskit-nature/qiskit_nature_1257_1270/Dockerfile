ARG BASE_IMAGE=benchmark-base:qiskit_nature_1257_1270
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_1257_1270
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/1257
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1270
ENV BASE_COMMIT=d59bdb2f88a7324fdfdb61283f56097d315a1afc
ENV PATCHED_COMMIT=27a14604f04484261a522fcf7865e16dcee639f5
ENV PR_HEAD_COMMIT=a9c72ff6cb7048998c9a087af1db53845ae90a03
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_no_num_modes test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_validate_16____2___2__False_ test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_no_validate test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_no_copy test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_compose test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_tensor test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_simplify test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_index_order test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_hermiticity test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_terms test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_from_polynomial_tensor test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_from_fermionic_op test/second_q/operators/test_majorana_op.py::TestMajoranaOp::test_permute_indices"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_from_polynomial_tensor test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_permute_indices test/second_q/operators/test_bosonic_op.py::TestBosonicOp::test_simplify test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_assign_parameters test/second_q/operators/test_polynomial_tensor.py::TestPolynomialTensor::test_compose test/second_q/operators/test_spin_op.py::TestSpinOp::test_terms test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_automatic_num_modals test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_no_num_spin_orbitals test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_compose test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_tensor test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_simplify test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_index_order test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_hermiticity test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_terms"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
