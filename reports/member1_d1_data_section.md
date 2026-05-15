# member1_d1_data_section.md

# D1 — Dataset and Gold Q/A Preparation

For D1, my role was preparing the dataset foundation for the Climate Evidence GraphRAG Agent. I focused on organizing the climate document metadata, preparing the initial gold Q/A set, and making sure the data is useful for retrieval evaluation later.

I prepared the metadata structure for 30 real climate PDFs. The documents include IPCC climate science reports, UNEP reports, COP28 and UNFCCC documents, UAE climate strategy documents, arXiv climate-AI papers, and other open-access climate or sustainability papers. For each document, I included climate-specific metadata such as countries, regions, sectors, climate risks, technologies, policies, targets, indicators, and topics.

I also prepared a gold Q/A set with 30 climate-focused questions. The questions cover climate policy, mitigation, adaptation, renewable energy, UAE climate initiatives, COP28, climate risks, and climate-AI topics. I also included adversarial/refusal questions to test if the system avoids answering unrelated questions.

For retrieval evaluation, each gold question is connected to a source document, page number or page range, and relevant chunk IDs once ingestion is completed. This will help the team check whether the retrieval system can find the correct evidence before generating an answer.

My D1 contribution supports the next stages of the project because the metadata and gold Q/A set will be used for hybrid retrieval, AutoML tuning, GraphRAG, citation verification, and final evaluation.