FROM benchmark-base:qiskit_optimization_13_163

ENV SAMPLE_ID=qiskit_optimization_13_163
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/13
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/163
ENV BASE_COMMIT=7a3ff2243d70c3b9e33fbaa87ffbd95a383774fa
ENV PATCHED_COMMIT=072b29f8d76081d524dc3f70f741efb0481d199c
ENV PR_HEAD_COMMIT=072b29f8d76081d524dc3f70f741efb0481d199c
ENV DEFAULT_TARGET=patched
ENV FAIL_PASS_TEST_PATHS="test/translators/test_docplex_mp.py::TestDocplexMpTranslator::test_indicator_constraints"
ENV PASS_PASS_TEST_PATHS="test/translators/test_docplex_mp.py::TestDocplexMpTranslator::test_from_and_to test/problems/test_quadratic_program.py::TestQuadraticProgram::test_constructor test/problems/test_quadratic_program.py::TestQuadraticProgram::test_variables_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_objective_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_linear_constraints_handling test/problems/test_quadratic_program.py::TestQuadraticProgram::test_quadratic_constraints_handling test/problems/test_linear_constraint.py::TestLinearConstraint::test_init test/problems/test_linear_expression.py::TestLinearExpression::test_evaluate test/problems/test_variable.py::TestVariable::test_init"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
