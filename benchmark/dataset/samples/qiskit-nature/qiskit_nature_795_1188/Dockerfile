ARG BASE_IMAGE=benchmark-base:qiskit_nature_795_1188
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_795_1188
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/795
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1188
ENV BASE_COMMIT=a8951eb0602cb32834cdbd3686c1d85569e8a409
ENV PATCHED_COMMIT=bade0896005e0df3a36bc71b6354c13f21e3c726
ENV PR_HEAD_COMMIT=bade0896005e0df3a36bc71b6354c13f21e3c726
ENV FAIL_PASS_TEST_PATHS="test/second_q/operators/test_mixed_op.py::TestFermionicOp::test_add test/second_q/operators/test_mixed_op.py::TestFermionicOp::test_compose test/second_q/operators/test_mixed_op.py::TestFermionicOp::test_div test/second_q/operators/test_mixed_op.py::TestFermionicOp::test_mul test/second_q/operators/test_mixed_op.py::TestFermionicOp::test_neg test/second_q/operators/test_mixed_op.py::TestFermionicOp::test_sub test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_map_list_or_dict_1 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_map_list_or_dict_2 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_map_list_or_dict_3 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_map_list_or_dict_4 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_map_multiple_fermionic_operators test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_relative_mapping_1 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_relative_mapping_2 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_relative_mapping_3 test/second_q/mappers/test_mixed_mapper.py::TestMixedMapper::test_relative_mapping_4"
ENV PASS_PASS_TEST_PATHS="test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_mul test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_add test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_sub test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_compose test/second_q/operators/test_fermionic_op.py::TestFermionicOp::test_tensor test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_single_op test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_list_ops test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping_for_dict_ops"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
