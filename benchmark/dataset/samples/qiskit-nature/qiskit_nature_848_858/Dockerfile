ARG BASE_IMAGE=benchmark-base:qiskit_nature_848_858
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_848_858
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/848
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/858
ENV BASE_COMMIT=d1af4bab5df10e4f56b670b342c9c1a60ea059e6
ENV PATCHED_COMMIT=abfd9973b316b8b33990c7aace0940b950b3ddab
ENV PR_HEAD_COMMIT=abfd9973b316b8b33990c7aace0940b950b3ddab
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_commutators.py::TestCommutators::test_anti_commutator_1 test/second_q/operators/test_commutators.py::TestCommutators::test_anti_commutator_2 test/second_q/operators/test_commutators.py::TestCommutators::test_commutator_1 test/second_q/operators/test_commutators.py::TestCommutators::test_commutator_2 test/second_q/operators/test_commutators.py::TestCommutators::test_double_commutator_1 test/second_q/operators/test_commutators.py::TestCommutators::test_double_commutator_2 test/second_q/operators/test_commutators.py::TestCommutators::test_double_commutator_3 test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_is_zero"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_add test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_adjoint test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_conjugate test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_copy test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_eq test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_equiv test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_get_item test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_iter test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_len test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_mul test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_one test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_zero"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
