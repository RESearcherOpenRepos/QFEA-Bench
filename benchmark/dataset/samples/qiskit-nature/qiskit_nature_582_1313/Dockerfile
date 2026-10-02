ARG BASE_IMAGE=benchmark-base:qiskit_nature_582_1313
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_582_1313
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/582
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1313
ENV BASE_COMMIT=07dcedcf7fb74f025177ef9c76366a264a1a955c
ENV PATCHED_COMMIT=1d9ed904c5337c8330a6d41b69fbfbabb5e5ec4e
ENV PR_HEAD_COMMIT=1d9ed904c5337c8330a6d41b69fbfbabb5e5ec4e
ENV FAIL_PASS_TEST_PATHS="test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_mapping test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_pauli_table test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_mapping_for_single_op test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_mapping_for_list_ops test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_mapping_for_dict_ops test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_mapping_overwrite_reg_len test/second_q/mappers/test_ternary_tree_mapper.py::TestTernaryTreeMapper::test_mapping_pauli_priority"
ENV PASS_PASS_TEST_PATHS="test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_single_op test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_list_ops test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_dict_ops test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_overwrite_reg_len"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
