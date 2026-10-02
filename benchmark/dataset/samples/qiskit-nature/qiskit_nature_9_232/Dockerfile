FROM benchmark-base:qiskit_nature_9_232

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_9_232
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/9
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/232
ENV BASE_COMMIT=1af22ae8675e591b84038cc1fa88db62ea8acb23
ENV PATCHED_COMMIT=28728860f9d6154a55bcda6a31936f7f26a25b33
ENV PR_HEAD_COMMIT=28728860f9d6154a55bcda6a31936f7f26a25b33
ENV FAIL_PASS_TEST_PATHS="test/mappers/second_quantization/test_bksf_mapper.py::TestBravyiKitaevSuperFastMapper::test_bksf_edge_op_bi test/mappers/second_quantization/test_bksf_mapper.py::TestBravyiKitaevSuperFastMapper::test_bksf_edge_op_aij test/mappers/second_quantization/test_bksf_mapper.py::TestBravyiKitaevSuperFastMapper::test_h2"
ENV PASS_PASS_TEST_PATHS="test/mappers/second_quantization/test_bravyi_kitaev_mapper.py::TestBravyiKitaevMapper::test_mapping test/mappers/second_quantization/test_bravyi_kitaev_mapper.py::TestBravyiKitaevMapper::test_allows_two_qubit_reduction test/mappers/second_quantization/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping test/mappers/second_quantization/test_parity_mapper.py::TestParityMapper::test_mapping test/mappers/second_quantization/test_parity_mapper.py::TestParityMapper::test_allows_two_qubit_reduction"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
