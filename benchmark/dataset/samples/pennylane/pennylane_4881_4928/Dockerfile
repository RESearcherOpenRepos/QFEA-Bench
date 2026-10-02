FROM benchmark-base:pennylane_4881_4928

ENV SAMPLE_ID=pennylane_4881_4928
ENV REPOSITORY_URL=https://github.com/PennyLaneAI/pennylane.git
ENV BASE_COMMIT=bb0bf88e311a6d89fc2ddb6f4a09f8dc7d63a4a7
ENV PATCHED_COMMIT=2b971e013bb5b962263a27e987c56371d75e9b3f
ENV FAIL_PASS_TEST_PATHS="tests/fermi/test_parity_mapping.py::test_error_is_raised_for_incompatible_type tests/fermi/test_parity_mapping.py::test_error_is_raised_for_dimension_mismatch tests/fermi/test_parity_mapping.py::test_warning_is_raised_with_use tests/fermi/test_parity_mapping.py::test_parity_transform_fermi_word_ps[fermionic_op4-4-result4] tests/fermi/test_parity_mapping.py::test_parity_transform_fermi_word_ps[fermionic_op8-6-result8] tests/fermi/test_parity_mapping.py::test_parity_transform_fermi_word_operation[fermionic_op4-4-result4] tests/fermi/test_parity_mapping.py::test_parity_transform_for_identity tests/fermi/test_parity_mapping.py::test_parity_transform_for_null_operator_fermi_word_ps[operator0] tests/fermi/test_parity_mapping.py::test_empty_fermi_sentence tests/fermi/test_parity_mapping.py::test_parity_transform_for_fermi_sentence_ps[fermionic_op0-4-result0] tests/fermi/test_parity_mapping.py::test_parity_transform_for_fermi_sentence_operation[fermionic_op0-4-result0] tests/fermi/test_parity_mapping.py::test_providing_wire_map_fermi_word_to_ps[wire_map1-ops1] tests/fermi/test_parity_mapping.py::test_providing_wire_map_fermi_sentence_to_operation[wire_map1-ops1] tests/fermi/test_parity_mapping.py::test_parity_transform_tolerance[fermi_op2-qubit_op_data2-1e-12]"
ENV PASS_PASS_TEST_PATHS="tests/fermi/test_fermi_mapping.py::test_error_is_raised_for_incompatible_type tests/fermi/test_fermi_mapping.py::test_jordan_wigner_fermi_word_ps[fermionic_op4-result4] tests/fermi/test_fermi_mapping.py::test_jordan_wigner_fermi_word_ps[fermionic_op8-result8] tests/fermi/test_fermi_mapping.py::test_jordan_wigner_fermi_word_operation[fermionic_op4-result4] tests/fermi/test_fermi_mapping.py::test_jordan_wigner_for_identity tests/fermi/test_fermi_mapping.py::test_jordan_wigner_for_null_operator_fermi_word_ps[operator0] tests/fermi/test_fermi_mapping.py::test_empty_fermi_sentence tests/fermi/test_fermi_mapping.py::test_jordan_wigner_for_fermi_sentence_ps[fermionic_op0-result0] tests/fermi/test_fermi_mapping.py::test_jordan_wigner_for_fermi_sentence_operation[fermionic_op0-result0] tests/fermi/test_fermi_mapping.py::test_providing_wire_map_fermi_word_to_ps[wire_map1-ops1] tests/fermi/test_fermi_mapping.py::test_providing_wire_map_fermi_sentence_to_operation[wire_map1-ops1] tests/fermi/test_fermi_mapping.py::test_jordan_wigner_tolerance[fermi_op2-qubit_op_data2-1e-12]"

WORKDIR /benchmark
COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
