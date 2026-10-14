resource "aws_dynamodb_table" "sightings" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sighting_id"

  attribute {
    name = "sighting_id"
    type = "S"
  }

  attribute {
    name = "query_key"
    type = "S"
  }

  attribute {
    name = "query_sort"
    type = "S"
  }

  global_secondary_index {
    name            = "query-by-key"
    hash_key        = "query_key"
    range_key       = "query_sort"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}
