# member1_d1_data_section.md

Write your own implementation details, decisions, results, screenshots, and failure cases here.

For D1, my role was preparing the dataset structure and the initial gold Q/A evaluation set for the Climate Evidence GraphRAG Agent project.

I worked on expanding the climate metadata file by adding more climate-related reports and policy documents such as UAE Net Zero 2050, COP28 UAE Consensus, IPCC AR6, and other climate and renewable energy reports. The metadata includes fields like countries, regions, climate risks, technologies, sectors, policies, and indicators. These fields will later help with retrieval, filtering, and GraphRAG tasks.

I also worked on the gold Q/A dataset and expanded it with around 30 climate-focused evaluation questions. The questions include topics related to climate policy, renewable energy, adaptation, mitigation, climate risks, UAE climate initiatives, and COP28. I also included a few adversarial questions to test whether the system can correctly refuse unrelated questions.

One challenge during D1 was that the ingestion pipeline was not implemented yet, so real page numbers and chunk IDs were not available. Because of this, placeholder values were temporarily used.

Overall, my contribution in D1 focused on building a clean and climate-specific dataset foundation that will support later retrieval evaluation, GraphRAG integration, and citation verification.