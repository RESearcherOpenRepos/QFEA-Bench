FROM benchmark-base:qiskit_nature_243_263

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_243_263
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/243
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/263
ENV BASE_COMMIT=e6a2dfd3c5039cb1c00c10540c2d76ca026f281c
ENV PATCHED_COMMIT=3a5a0294032145a54ac53ee2e1fb8358aa291f1d
ENV PR_HEAD_COMMIT=3a5a0294032145a54ac53ee2e1fb8358aa291f1d
ENV FAIL_PASS_TEST_PATHS="test/properties/second_quantization/electronic/integrals/test_integral_property.py::TestIntegralProperty::test_init test/properties/second_quantization/electronic/integrals/test_integral_property.py::TestIntegralProperty::test_get_electronic_int test/properties/second_quantization/electronic/integrals/test_integral_property.py::TestIntegralProperty::test_transform_basis test/properties/second_quantization/electronic/integrals/test_integral_property.py::TestIntegralProperty::test_second_q_ops"
ENV PASS_PASS_TEST_PATHS="test/properties/second_quantization/electronic/integrals/test_one_body_electronic_integrals.py::TestOneBodyElectronicIntegrals::test_init test/properties/second_quantization/electronic/integrals/test_one_body_electronic_integrals.py::TestOneBodyElectronicIntegrals::test_to_spin test/properties/second_quantization/electronic/integrals/test_one_body_electronic_integrals.py::TestOneBodyElectronicIntegrals::test_to_second_q_op test/properties/second_quantization/electronic/integrals/test_two_body_electronic_integrals.py::TestTwoBodyElectronicIntegrals::test_init test/properties/second_quantization/electronic/integrals/test_two_body_electronic_integrals.py::TestTwoBodyElectronicIntegrals::test_to_spin test/properties/second_quantization/electronic/integrals/test_two_body_electronic_integrals.py::TestTwoBodyElectronicIntegrals::test_to_second_q_op"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
