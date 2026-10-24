#include "GeoreferencedNode.h"
#include "Models/CesiumGlobe.h"
#include "Utils/CesiumMathUtils.h"
#include "glm/ext/vector_double3.hpp"
#include "godot_cpp/classes/engine.hpp"
#include "godot_cpp/classes/tile_set.hpp"


void GeoreferencedMesh::_ready() {
	if (Engine::get_singleton()->is_editor_hint()) return;

	const CesiumGeoreference* georeference = this->get_georeference();
	// True origin is a no-op
	if (georeference->get_origin_type_raw() == CesiumGeoreference::OriginType::TrueOrigin) {
		return;
	}
	// The node was placed relative to the georeference's origin, so its ECEF position is the origin plus its offset
	const glm::dvec3 ecefOffset = georeference->unshifted_engine_to_ecef(CesiumMathUtils::to_glm_dvec3(this->get_global_position()));
	this->set_ecef_position_precise(georeference->get_ecef_position() + ecefOffset);
}

void GeoreferencedMesh::apply_position_on_globe(const glm::dvec3& engineOrigin) {
	glm::dvec3 globalPos = this->m_originalPosition - engineOrigin;
	this->set_global_position(CesiumMathUtils::from_glm_vec3(globalPos));
}

const glm::dvec3& GeoreferencedMesh::get_original_position() const {
	return this->m_originalPosition;
}

void GeoreferencedMesh::set_original_position(const glm::dvec3& position) {
	this->m_originalPosition = position;
}

void GeoreferencedMesh::set_engine_position(const Vector3& position) {
	const CesiumGeoreference* georef = this->m_tileset->get_georeference_node();
	this->m_originalPosition = CesiumMathUtils::to_glm_dvec3(position);
	this->apply_position_on_globe(georef->get_unshifted_engine_origin());
}

void GeoreferencedMesh::set_ecef_position(const Vector3& position) {
	this->set_ecef_position_precise(CesiumMathUtils::to_glm_dvec3(position));
}

void GeoreferencedMesh::set_ecef_position_precise(const glm::dvec3& position) {
	const CesiumGeoreference* georef = this->m_tileset->get_georeference_node();
	this->m_originalPosition = georef->ecef_to_unshifted_engine(position);
	this->apply_position_on_globe(georef->get_unshifted_engine_origin());
}


Vector3 GeoreferencedMesh::get_ecef_position() const {
	return CesiumMathUtils::from_glm_vec3(this->m_tileset->get_georeference_node()->unshifted_engine_to_ecef(this->m_originalPosition));
}

void GeoreferencedMesh::set_tileset(Cesium3DTileset* tileset) {
	this->m_tileset = tileset;
}


void GeoreferencedMesh::set_tileset_no_reparent(Cesium3DTileset* tileset) {
	this->m_tileset = tileset;
}

Vector3 GeoreferencedMesh::get_engine_position() const {
	return CesiumMathUtils::from_glm_vec3(this->m_originalPosition);
}


Cesium3DTileset* GeoreferencedMesh::get_tileset() const {
	return this->m_tileset;
}

CesiumGeoreference* GeoreferencedMesh::get_georeference() const {
	return this->m_tileset->get_georeference_node();
}


void GeoreferencedMesh::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_engine_position"), &GeoreferencedMesh::get_engine_position);
    ClassDB::bind_method(D_METHOD("set_engine_position", "position"), &GeoreferencedMesh::set_engine_position);
    ClassDB::bind_method(D_METHOD("get_ecef_position"), &GeoreferencedMesh::get_ecef_position);
    ClassDB::bind_method(D_METHOD("set_ecef_position", "position"), &GeoreferencedMesh::set_ecef_position);
    ClassDB::bind_method(D_METHOD("set_tileset", "tileset"), &GeoreferencedMesh::set_tileset);
    ClassDB::bind_method(D_METHOD("get_tileset"), &GeoreferencedMesh::get_tileset);
    ClassDB::bind_method(D_METHOD("get_georeference"), &GeoreferencedMesh::get_georeference);
	ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "tileset", PropertyHint::PROPERTY_HINT_NODE_TYPE, "Cesium3DTileset"), "set_tileset", "get_tileset");
}

