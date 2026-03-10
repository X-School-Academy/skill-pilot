Please check the whole project and docs, then for each feature, create feature file at core/features/xx-xx.md

the feature file should
1. file name only contains lower chars and `-`
2. a short brif the the featue description 
3. code reference: only have file name related to root of the project, and function names, keywords (no line number)

the feature file will help user and AI to quick understand the feature functions and located the code file/block location

as the AI will use find/grep/ripgrep/sed/cat to inspect the code, so we need to make sure 

1. the feature file size should be smaller enough to save LLM context window
2. have enough keywords for LLM to use tools to inspect the related code

The a feature should be from user level. or no-tech user level, unless it is really a tech only related feature
each feature should be not too small, as it is hard to llm only to check a function with exact line numer info, so it may read large chunck of code, 
in the webui, all the left menu item can be a feature, for a large feature, we may have sub feature, for sub feature, it should be named as feature-name--sub-feature-name.md (Double Hyphen)