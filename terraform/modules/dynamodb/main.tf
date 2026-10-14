resource "aws_dynamodb_table" "sightings" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sighting_id"

  attribute {
    name = "sighting_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}
