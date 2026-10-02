ARG BASE_IMAGE=benchmark-base:qiskit_nature_669_731
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_669_731
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/669
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/731
ENV BASE_COMMIT=30a6852ee0082805399f05077014701be9645c4b
ENV PATCHED_COMMIT=a4ea55a2bfee90260eb97fbd5eb60673350f6a90
ENV PR_HEAD_COMMIT=0cf68ff4cdf45cc8425f54a57a3cb7d42743be56
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_add test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_mul test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_adjoint test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_conjugate test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_eq test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_equiv test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_iter test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_get_item test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_len test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_get_register_length test/second_q/operators/test_sparse_label_op.py::TestSparseLabelOp::test_copy"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_register_length test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_mul test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_add test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_adjoint test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_equiv test/second_q/operators/test_spin_op.py::TestSpinOp::test_mul test/second_q/operators/test_spin_op.py::TestSpinOp::test_add test/second_q/operators/test_spin_op.py::TestSpinOp::test_adjoint test/second_q/operators/test_spin_op.py::TestSpinOp::test_equiv test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_mul test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_add test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_equiv"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
