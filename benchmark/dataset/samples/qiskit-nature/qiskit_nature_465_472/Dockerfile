ARG BASE_IMAGE=benchmark-base:qiskit_nature_465_472
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_465_472
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/465
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/472
ENV BASE_COMMIT=3c86e4d2b38947b40aca29bf88882055761c208a
ENV PATCHED_COMMIT=95167df7f543b5bfda357127e8d56492801c30b0
ENV PR_HEAD_COMMIT=95167df7f543b5bfda357127e8d56492801c30b0
ENV FAIL_PASS_TEST_PATHS="test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_from_networkx"
ENV PASS_PASS_TEST_PATHS="test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_init test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_from_nodes_and_edges test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_to_adjacency_matrix test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_nonnumeric_weight_raises test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_copy test/problems/second_quantization/lattice/lattices/test_lattice.py::TestLattice::test_edges_removed"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
