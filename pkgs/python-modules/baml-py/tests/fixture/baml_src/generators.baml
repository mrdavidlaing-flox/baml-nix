generator target {
  output_type "python/pydantic"
  output_dir "../"
  // Must match the installed baml-py version exactly.
  version "0.226.3"
  default_client_mode sync
}
