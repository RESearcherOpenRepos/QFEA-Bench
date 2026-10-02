ARG BASE_IMAGE=benchmark-base:qiskit_nature_493_506
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_493_506
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/493
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/506
ENV BASE_COMMIT=508b81f45f996d300a2a6b2051d1678334b9ed82
ENV PATCHED_COMMIT=18bcd28a17cb4765a48cfd6af2926f62c8c7cc18
ENV PR_HEAD_COMMIT=18bcd28a17cb4765a48cfd6af2926f62c8c7cc18
ENV FAIL_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_from_tuple_label"
ENV PASS_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_multiple_digits test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_register_length test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_add"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
