ARG BASE_IMAGE=benchmark-base:qiskit_nature_828_891
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_828_891
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/828
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/891
ENV BASE_COMMIT=a57992859df038541e7938faf8fdb52db600f7e4
ENV PATCHED_COMMIT=a56898c8a32e15373bd9ff4fe830bffc104fe43c
ENV PR_HEAD_COMMIT=a56898c8a32e15373bd9ff4fe830bffc104fe43c
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_assign_parameters test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_chop test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_equiv test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_induced_norm test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_is_parameterized test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_mul test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_parameters test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_compose test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_div test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_hermiticity test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_mul test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_normal_order test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_pow test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_simplify test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_to_matrix test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_single_op"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_add test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_adjoint test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_copy test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_eq test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_get_item test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_add test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_adjoint test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_expand"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
