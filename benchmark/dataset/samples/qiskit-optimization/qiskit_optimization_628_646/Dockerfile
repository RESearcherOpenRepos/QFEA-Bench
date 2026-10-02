ARG BASE_IMAGE=benchmark-base:qiskit_optimization_628_646
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_optimization_628_646
ENV REPOSITORY=qiskit-community/qiskit-optimization
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-optimization.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-optimization/issues/628
ENV PR_URL=https://github.com/qiskit-community/qiskit-optimization/pull/646
ENV BASE_COMMIT=c4487cc9b51ef990c8b9f750fc2512c28177ef1c
ENV PATCHED_COMMIT=53184abdc05965e12a5de9e2d1e3ecc1ce64fedf
ENV PR_HEAD_COMMIT=c69874b7c934e48037329afbb8d28bb5e9b97229
ENV FAIL_PASS_TEST_PATHS=test/applications/test_tsp.py::TestTspCustomGraph::test_to_quadratic_program
ENV PASS_PASS_TEST_PATHS="test/applications/test_tsp.py::TestTsp::test_create_random_instance test/applications/test_tsp.py::TestTsp::test_edgelist test/applications/test_tsp.py::TestTsp::test_interpret test/applications/test_tsp.py::TestTsp::test_parse_tsplib_format test/applications/test_tsp.py::TestTsp::test_to_quadratic_program test/applications/test_vehicle_routing.py::TestVehicleRouting::test_edgelist test/applications/test_vehicle_routing.py::TestVehicleRouting::test_interpret test/applications/test_vehicle_routing.py::TestVehicleRouting::test_to_quadratic_program test/applications/test_max_cut.py::TestMaxcut::test_to_quadratic_program test/applications/test_knapsack.py::TestKnapsack::test_to_quadratic_program"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
