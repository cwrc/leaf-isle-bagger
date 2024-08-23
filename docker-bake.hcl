target "leaf-bagger" {
  dockerfile = "Dockerfile"
  args = {
    BAGGER_TAG = "v0.0.5@sha256:4e05219adb36595ddfc51fee33a35ead45fced6b01f57e157bcc01d2608a4aae"
  } 
}
