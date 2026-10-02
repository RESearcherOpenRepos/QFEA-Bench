ARG BASE_IMAGE=benchmark-base:qiskit_optimization_433_467
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_433_467
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/433
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/467
ENV BASE_COMMIT=07b75acc7ce16a95354ecb2985c2df704e76802f
ENV PATCHED_COMMIT=e360343dbbd25790a294d6bee980244d7238f903
ENV PR_HEAD_COMMIT=e360343dbbd25790a294d6bee980244d7238f903
ENV FAIL_PASS_TEST_PATHS="test/translators/test_ising.py::TestIsingTranslator::test_from_ising2_2_False test/translators/test_ising.py::TestIsingTranslator::test_from_ising_2_False test/translators/test_ising.py::TestIsingTranslator::test_from_ising_pauli_with_invalid_paulis_2_False test/translators/test_ising.py::TestIsingTranslator::test_pauli_I_Z_2_False test/translators/test_ising.py::TestIsingTranslator::test_to_ising2_2_False test/translators/test_ising.py::TestIsingTranslator::test_to_ising_2_False test/translators/test_ising.py::TestIsingTranslator::test_to_ising_wo_variable_2_False test/translators/test_ising.py::TestIsingTranslator::test_warning"
ENV PASS_PASS_TEST_PATHS="test/converters/test_converters.py::TestConverters::test_empty_problem test/converters/test_converters.py::TestConverters::test_valid_variable_type test/converters/test_converters.py::TestConverters::test_optimizationproblem_to_ising test/converters/test_converters.py::TestConverters::test_ising_to_quadraticprogram_linear test/converters/test_converters.py::TestConverters::test_ising_to_quadraticprogram_quadratic"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
