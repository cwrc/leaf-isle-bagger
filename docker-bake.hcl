target "leaf-bagger" {
  dockerfile = "Dockerfile"
  args = {
    BAGGER_TAG = "v0.0.4@sha256:668e47efe49280eeef0b004eb11a2d380804d02e333ad24568061e846fe7fb80"
  } 
}
