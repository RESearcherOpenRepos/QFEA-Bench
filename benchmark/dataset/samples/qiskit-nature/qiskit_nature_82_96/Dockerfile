ARG BASE_IMAGE=benchmark-base:qiskit_nature_82_96
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_82_96
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/82
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/96
ENV BASE_COMMIT=8a5849a71671107841db956af81ecc098424d109
ENV PATCHED_COMMIT=1d0d3d3579a06463e3a2f35ffa31f4746354c438
ENV FAIL_PASS_TEST_PATHS="test/operators/second_quantization/test_qubit_converter.py::TestQubitConverter::test_two_qubit_reduction test/operators/second_quantization/test_qubit_converter.py::TestQubitConverter::test_z2_symmetry test/operators/second_quantization/test_qubit_converter.py::TestQubitConverter::test_two_qubit_reduction_and_z2_symmetry"
ENV PASS_PASS_TEST_PATHS="test/mappers/second_quantization/test_parity_mapper.py::TestParityMapper::test_allows_two_qubit_reduction test/mappers/second_quantization/test_parity_mapper.py::TestParityMapper::test_mapping test/mappers/second_quantization/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_allows_two_qubit_reduction test/mappers/second_quantization/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
