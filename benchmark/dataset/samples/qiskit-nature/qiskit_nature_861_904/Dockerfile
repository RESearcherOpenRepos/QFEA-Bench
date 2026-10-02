ARG BASE_IMAGE=benchmark-base:qiskit_nature_861_904
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_861_904
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/861
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/904
ENV BASE_COMMIT=dff4a30581f0451ae970525cbbc54bb0c6b0e4d9
ENV PATCHED_COMMIT=aedf3472e2e6f3e729204c099503fefd073c9d2b
ENV PR_HEAD_COMMIT=aedf3472e2e6f3e729204c099503fefd073c9d2b
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_round"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_add test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_adjoint test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_conjugate test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_copy test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_eq test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_equiv test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_get_item test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_is_zero test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_iter test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_len test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_mul test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_one test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_zero test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_add test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_div test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_equiv test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_hermiticity test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_mul test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_neg test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_simplify"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
