ARG BASE_IMAGE=benchmark-base:qiskit_nature_271_286
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_271_286
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/271
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/286
ENV BASE_COMMIT=7a8b3923c5718cdda62b05f14ccd260b73564e76
ENV PATCHED_COMMIT=df73128801f5653b2a76cd68eab9059649a2d1bb
ENV FAIL_PASS_TEST_PATHS="test/converters/second_quantization/test_qubit_converter.py::TestQubitConverter::test_two_qubit_reduction"
ENV PASS_PASS_TEST_PATHS="test/mappers/second_quantization/test_parity_mapper.py::TestParityMapper::test_allows_two_qubit_reduction test/mappers/second_quantization/test_parity_mapper.py::TestParityMapper::test_mapping test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_init_multiple_digits test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_mul test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_add test/operators/second_quantization/test_fermionic_op.py::TestFermionicOp::test_reduce"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
