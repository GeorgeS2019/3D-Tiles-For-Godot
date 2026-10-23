extends SceneTree

# Run in a Godot project containing the addon, after importing it headlessly.
func _init() -> void:
	var success := true
	for class_name_to_check in ["CesiumGeoreference", "Cesium3DTileset", "CesiumIonRasterOverlay"]:
		var registered := ClassDB.class_exists(class_name_to_check)
		print(class_name_to_check, " registered: ", registered)
		success = success and registered
	quit(0 if success else 1)
