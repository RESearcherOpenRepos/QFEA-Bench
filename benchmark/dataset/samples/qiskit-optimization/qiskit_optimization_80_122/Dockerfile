ARG BASE_IMAGE=benchmark-base:qiskit_optimization_80_122
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_80_122
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/80
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/122
ENV BASE_COMMIT=b661c54807660cea0e0e3a4260e61988bb575fa2
ENV PATCHED_COMMIT=cfe0b8230d62bf6e652f16cc7f91d769a5eedea9
ENV PR_HEAD_COMMIT=cfe0b8230d62bf6e652f16cc7f91d769a5eedea9
ENV FAIL_PASS_TEST_PATHS="test/translators/test_docplex_mp.py::TestDocplexMpTranslator::test_from_and_to"
ENV FAIL_PASS_SUPPORT_PATHS="test/translators/__init__.py"
ENV PASS_PASS_TEST_PATHS="test/problems/test_quadratic_program.py::TestQuadraticProgram::test_constructor test/problems/test_quadratic_program.py::TestQuadraticProgram::test_docplex test/problems/test_quadratic_program.py::TestQuadraticProgram::test_linear_constraints_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_objective_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_quadratic_constraints_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_variables_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_write_to_lp_file"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
