ARG BASE_IMAGE=benchmark-base:qiskit_nature_6_624
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_6_624
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/6
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/624
ENV BASE_COMMIT=c89e2cc151dc832b8d7ceee720abfe5af8147753
ENV PATCHED_COMMIT=7964402599ae7096b58936ee59dbec49697ee2c3
ENV PR_HEAD_COMMIT=7964402599ae7096b58936ee59dbec49697ee2c3
ENV FAIL_PASS_TEST_PATHS="test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_1 test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_2 test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_3 test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_4 test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_5 test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_6 test/mappers/second_quantization/test_logarithmic_mapper.py::TestLogarithmicMapper::test_mapping_7"
ENV PASS_PASS_TEST_PATHS="test/mappers/second_quantization/test_linear_mapper.py::TestLinearMapper::test_mapping_1 test/mappers/second_quantization/test_linear_mapper.py::TestLinearMapper::test_mapping_2 test/mappers/second_quantization/test_linear_mapper.py::TestLinearMapper::test_mapping_3 test/mappers/second_quantization/test_linear_mapper.py::TestLinearMapper::test_mapping_4 test/mappers/second_quantization/test_linear_mapper.py::TestLinearMapper::test_mapping_5"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
