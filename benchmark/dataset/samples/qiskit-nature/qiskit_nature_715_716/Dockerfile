ARG BASE_IMAGE=benchmark-base:qiskit_nature_715_716
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_715_716
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/715
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/716
ENV BASE_COMMIT=efab7e03cfc1904fdff49dd13ed7386bb2fb91ce
ENV PATCHED_COMMIT=2844bba54f0f9355d1d2e0119fa5e461f7e7baaa
ENV PR_HEAD_COMMIT=59d72e49297f7a45a6648fdb7be2db06dc86842f
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_equiv test/second_q/operators/test_spin_op.py::TestSpinOp::test_equiv test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_equiv"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_hermiticity test/second_q/operators/test_spin_op.py::TestSpinOp::test_hermiticity test/second_q/operators/test_vibrational_op.py::TestVibrationalOp::test_simplify"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
