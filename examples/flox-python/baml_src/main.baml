// A client that is never called: the tests only generate and import.
client<llm> Fake {
  provider openai
  options {
    model "gpt-4o-mini"
    api_key "unused"
  }
}

class Resume {
  name string
  skills string[]
}

function ExtractResume(text: string) -> Resume {
  client Fake
  prompt #"
    Extract the resume from:
    {{ text }}

    {{ ctx.output_format }}
  "#
}
