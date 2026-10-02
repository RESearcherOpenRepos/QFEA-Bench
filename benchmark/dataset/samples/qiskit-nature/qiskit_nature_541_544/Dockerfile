ARG BASE_IMAGE=benchmark-base:qiskit_nature_541_544
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_541_544
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/541
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/544
ENV BASE_COMMIT=3a44a3424501152f7870d1718e45cfc2fd2375c2
ENV PATCHED_COMMIT=9ed79a56cf4205f3bb1e1ca8310414c021cb71a1
ENV PR_HEAD_COMMIT=9ed79a56cf4205f3bb1e1ca8310414c021cb71a1
ENV FAIL_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_terms"
ENV PASS_PASS_TEST_PATHS="test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_from_tuple_label test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_register_length test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_mul test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_add"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
