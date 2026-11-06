generator target {
  output_type "python/pydantic"
  output_dir "../"
  // Filled in from baml-py.version by ../../generate.nix.
  version "@version@"
  default_client_mode sync
}
