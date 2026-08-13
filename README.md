# Privacy-preserving, transparent AI-assistance for writing letters (letter-ai)

`letter-ai` is a pip-installable command-line tool for privately reading past letters and drafting new ones using a locally installed large language model (LLM). Under the hood it uses pre-existing letters and corresponding summary text files for [few-shot prompting](https://en.wikipedia.org/wiki/Prompt_engineering#Multi-shot). Below you find instructions how to setup a database of synthetic letters to avoid using personal data directly for prompting and to avoid [information leakage](https://en.wikipedia.org/wiki/Information_leakage).

![](docs/teaser.png)

Note: This is a research tool not intended for production use.

## Privacy first

Letter-ai uses a local LLM per default for privacy reasons. The default is to use [Ollama](https://ollama.com) with `gemma3:4b`; this keeps personal letters on your machine. It is not recommended to use remote servers for such purposes, in particular if you don't know what the remote service provider does with the data you send there.

To setup a folder of example letters that do not contain any information about real people, follow this workflow:

1. Read letters you wrote in the past with `letter-ai read old-letter.docx`. It will extract the text from the letters, categorize the letter and summarize the content. Text and summary are saved in the folder `~/.letter-ai`. 
2. Write some "request.txt" files with random content, e.g. bullet points for a recommendation letter. Draft a new letter with `letter-ai write request.txt`. Do this multiple times with multiple contents to generate a base of letters with randomish content. 
4. Modify the generated DOCX to fit your needs and facts.
5. Delete the source letters containing information from actual people from the folder `~/.letter-ai` once you are done.
6. Pass the AI-generated letters using `letter-ai read old-letter.docx`
7. Finally go through all .txt files in `~/.letter-ai` and make sure that they do not contain any personal information.

Following this strategy, only the AI-generated synnthetic letters and summaries are stored in letter-ai's database of example letters. 

Alternatively, if you don't want to use letters about real people at all, consider AI-generating letters as demonstrated in [generate_mock_letters.ipynb](docs/generate_mock_letters.ipynb).

Overall the goal should be to have no personal data in the long-term storage `~/.letter-ai` and still be able to generate letters that use phrases of the human author.

![](docs/schematic.png)

## Usage

Write bullet points about the project or person you want to write a letter for/about in a textr file, e.g. `request.txt.

Afterwards, run this command to AI-generate a letter and open it with Word:

```bash
letter-ai write request.txt
```

You can also specify a `template.docx` file an the output location:

```bash
letter-ai write request.txt --template template.docx --output generated-letter.docx
```


## Installation

```bash
git clone https://github.com/haesleinhuepf/letter-ai

pip install .
```

For development, use `pip install -e .`.

## Ollama setup

Install Ollama, then pull the default model:

```bash
ollama pull gemma3:4b
```

Override the model or OpenAI-compatible endpoint with environment variables:

```bash
set LETTER_AI_MODEL=gemma3:4b
set LETTER_AI_BASE_URL=http://localhost:11434/v1
set LETTER_AI_API_KEY=ollama
```

On macOS/Linux, use `export` instead of `set`.

## Commands

Read. summarize and archive a DOCX letter:

```bash
letter-ai read support-letter.docx
```

This extracts the document body, classifies it as a support letter, recommendation letter, letter of intent, review report, or other, writes a concise bullet summary, and stores both files in `~/.letter-ai` using names such as `supportletter1.txt` and `supportletter1_summary.txt`.

Draft a new letter from a request file:

```bash
letter-ai write request.txt --template template.docx --output generated-letter.docx
```

The writer uses summaries and matching archived letters as few-shot examples. A template can be supplied with `--template`; otherwise `~/.letter-ai/default-template.docx` is used when present, and then a blank DOCX is created. Each generated document includes the model, base URL, and a link to this project.

Run `letter-ai --help` or `letter-ai read --help` for all options.

## Contributing

Contributions are welcome! Consider to open an issue first, before submitting a Pull Request.
Most of the code in this repository was vibe-coded using Github copilot integration in Visual Studio Code. When modifying code here, consider using a similar tool. 
