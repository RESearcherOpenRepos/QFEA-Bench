ARG BASE_IMAGE=benchmark-base:qiskit_nature_918_1046
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_918_1046
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/918
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1046
ENV BASE_COMMIT=38db50085fbbbaebe858dc80d18bd601545f0c02
ENV PATCHED_COMMIT=4b5426480044ffaebcdb945bf0c8bc435345091b
ENV PR_HEAD_COMMIT=4b5426480044ffaebcdb945bf0c8bc435345091b
ENV FAIL_PASS_TEST_PATHS="test/second_q/mappers/test_interleaved_qubit_mapper.py::TestInterleavedQubitMapper::test_mapping"
ENV PASS_PASS_TEST_PATHS="test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_allows_two_qubit_reduction test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_dict_ops test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_list_ops test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_single_op test/second_q/mappers/test_parity_mapper.py::TestParityMapper::test_allows_two_qubit_reduction test/second_q/mappers/test_parity_mapper.py::TestParityMapper::test_mapping_for_single_op test/second_q/mappers/test_bravyi_kitaev_mapper.py::TestBravyiKitaevMapper::test_allows_two_qubit_reduction test/second_q/mappers/test_bravyi_kitaev_mapper.py::TestBravyiKitaevMapper::test_mapping_for_single_op"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
