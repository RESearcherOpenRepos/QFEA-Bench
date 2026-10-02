ARG BASE_IMAGE=benchmark-base:qiskit_nature_683_684
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_683_684
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/683
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/684
ENV BASE_COMMIT=0f07057c4f72c026e6cde420bd8d7a112127fd70
ENV PATCHED_COMMIT=64b08facfb29cffb3cff91df65debb039bb6ee44
ENV PR_HEAD_COMMIT=64b08facfb29cffb3cff91df65debb039bb6ee44
ENV FAIL_PASS_TEST_PATHS="test/algorithms/pes_samplers/test_bopes_sampler.py::TestBOPES::test_h2_bopes_sampler_excited_eigensolver"
ENV PASS_PASS_TEST_PATHS="test/algorithms/pes_samplers/test_bopes_sampler.py::TestBOPES::test_h2_bopes_sampler test/algorithms/pes_samplers/test_bopes_sampler.py::TestBOPES::test_potential_interface"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
