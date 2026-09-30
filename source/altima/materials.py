"""Physically based material library for the Altima asset.

Every material is a Principled BSDF.  Car paint gets a real clearcoat layer
(+ a subtle flake roughness break-up driven by procedural noise, which renders
in Cycles/EEVEE but is ignored by glTF, where the flat PBR values are used).

MATERIALS maps the short key used by the generator to the spec tuple:
    (blender name, base_color_srgb, metallic, roughness, coat, coat_rough,
     transmission, sheen, emission_color, emission_strength)
"""

import bpy

MATERIALS = {
    # ---- paint ----------------------------------------------------------
    "paint_gold":     ("MAT_Paint_Gold_Metallic", (0.780, 0.640, 0.300), 0.85, 0.30, 1.00, 0.030, 0.0, 0.0, None, 0.0),
    "paint_gold_dk":  ("MAT_Paint_Gold_Jambs",    (0.660, 0.530, 0.240), 0.80, 0.38, 0.60, 0.060, 0.0, 0.0, None, 0.0),
    "paint_under":    ("MAT_Underbody_SeamSealer",(0.130, 0.125, 0.118), 0.00, 0.72, 0.00, 0.00,  0.0, 0.0, None, 0.0),

    # ---- glass ----------------------------------------------------------
    "glass_tint":     ("MAT_Glass_SolarTint",     (0.520, 0.660, 0.560), 0.00, 0.020, 0.0, 0.00, 1.0, 0.0, None, 0.0),
    "glass_clear":    ("MAT_Glass_Clear_HT",      (0.780, 0.860, 0.820), 0.00, 0.015, 0.0, 0.00, 1.0, 0.0, None, 0.0),
    "lamp_clear":     ("MAT_Lamp_Lens_PC",        (0.880, 0.900, 0.910), 0.00, 0.050, 0.40, 0.05, 0.0, 0.0, None, 0.0),
    "lamp_red":       ("MAT_Tail_Red",            (0.520, 0.045, 0.040), 0.00, 0.080, 0.60, 0.04, 0.0, 0.0, (0.60, 0.02, 0.02), 0.25),
    "lamp_amber":     ("MAT_Signal_Amber",        (0.760, 0.360, 0.040), 0.00, 0.080, 0.60, 0.04, 0.0, 0.0, (0.70, 0.28, 0.02), 0.15),
    "lamp_white":     ("MAT_Reverse_White",       (0.830, 0.830, 0.820), 0.00, 0.080, 0.60, 0.04, 0.0, 0.0, None, 0.0),
    "lamp_reflect":   ("MAT_Reflector_Chrome",    (0.900, 0.900, 0.905), 1.00, 0.060, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "lamp_bulb":      ("MAT_Bulb_Glass",          (0.920, 0.880, 0.780), 0.00, 0.070, 0.00, 0.00, 1.0, 0.0, (1.0, 0.85, 0.55), 3.0),

    # ---- brightwork / metals -------------------------------------------
    "chrome":         ("MAT_Chrome_Trim",         (0.900, 0.905, 0.910), 1.00, 0.055, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "chrome_brush":   ("MAT_Chrome_Brushed",      (0.780, 0.782, 0.786), 1.00, 0.240, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "steel":          ("MAT_Steel_Structural",    (0.480, 0.485, 0.492), 1.00, 0.380, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "steel_phos":     ("MAT_Steel_Phosphate_Fastener", (0.330, 0.330, 0.335), 1.00, 0.450, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "aluminium":      ("MAT_Aluminium_Cast",      (0.720, 0.730, 0.742), 1.00, 0.330, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "alu_brushed":    ("MAT_Aluminium_Brushed",   (0.760, 0.768, 0.778), 1.00, 0.220, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "cast_iron":      ("MAT_CastIron_Exhaust",    (0.235, 0.228, 0.222), 1.00, 0.680, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "stainless":      ("MAT_Stainless_Exhaust",   (0.620, 0.625, 0.632), 1.00, 0.280, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "copper":         ("MAT_Copper_Wire",         (0.700, 0.330, 0.150), 1.00, 0.320, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "brass":          ("MAT_Brass_Fitting",       (0.680, 0.510, 0.190), 1.00, 0.290, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "zinc":           ("MAT_Zinc_Plated",         (0.640, 0.645, 0.655), 1.00, 0.360, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "brake_disc":     ("MAT_BrakeDisc_GreyIron",  (0.300, 0.298, 0.300), 1.00, 0.560, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "battery_post":   ("MAT_Battery_Terminal",    (0.700, 0.680, 0.640), 1.00, 0.400, 0.00, 0.00, 0.0, 0.0, None, 0.0),

    # ---- rubbers / plastics --------------------------------------------
    "rubber":         ("MAT_Rubber_EPDM_Seal",    (0.045, 0.045, 0.048), 0.00, 0.830, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "rubber_hose":    ("MAT_Rubber_Hose",         (0.060, 0.058, 0.060), 0.00, 0.760, 0.10, 0.10, 0.0, 0.15, None, 0.0),
    "tire":           ("MAT_Tire_Compound",       (0.038, 0.038, 0.040), 0.00, 0.880, 0.00, 0.00, 0.0, 0.25, None, 0.0),
    "tire_tread":     ("MAT_Tire_Tread",          (0.030, 0.030, 0.032), 0.00, 0.920, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "plastic_blk_g":  ("MAT_Plastic_Black_Gloss", (0.030, 0.030, 0.033), 0.00, 0.180, 0.50, 0.05, 0.0, 0.0, None, 0.0),
    "plastic_blk_m":  ("MAT_Plastic_Black_Matte", (0.032, 0.032, 0.034), 0.00, 0.620, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "plastic_grey":   ("MAT_Plastic_Grey_Semi",   (0.245, 0.248, 0.255), 0.00, 0.450, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "plastic_dk":     ("MAT_Plastic_DarkGrey",    (0.090, 0.092, 0.097), 0.00, 0.520, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "plastic_light":  ("MAT_Plastic_LightGrey",   (0.480, 0.485, 0.490), 0.00, 0.480, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "plastic_ivory":  ("MAT_Plastic_Ivory",       (0.720, 0.700, 0.660), 0.00, 0.470, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "abs_wood":       ("MAT_Interior_Wood_Trim",  (0.230, 0.130, 0.062), 0.10, 0.190, 0.70, 0.04, 0.0, 0.0, None, 0.0),

    # ---- interior -------------------------------------------------------
    "fabric_grey":    ("MAT_Fabric_Grey_Cloth",   (0.185, 0.188, 0.195), 0.00, 0.860, 0.00, 0.00, 0.0, 0.60, None, 0.0),
    "fabric_dk":      ("MAT_Fabric_Dark_Cloth",   (0.075, 0.076, 0.080), 0.00, 0.900, 0.00, 0.00, 0.0, 0.60, None, 0.0),
    "vinyl_dash":     ("MAT_Vinyl_Dashboard",     (0.072, 0.074, 0.078), 0.00, 0.640, 0.00, 0.00, 0.0, 0.12, None, 0.0),
    "carpet":         ("MAT_Carpet_Pile",         (0.055, 0.056, 0.060), 0.00, 0.930, 0.00, 0.00, 0.0, 0.75, None, 0.0),
    "headliner":      ("MAT_Headliner_Cloth",     (0.420, 0.420, 0.415), 0.00, 0.900, 0.00, 0.00, 0.0, 0.55, None, 0.0),
    "seat_leather":   ("MAT_Leather_Beige",       (0.360, 0.315, 0.250), 0.00, 0.560, 0.20, 0.10, 0.0, 0.25, None, 0.0),

    # ---- powertrain -----------------------------------------------------
    "engine_alu":     ("MAT_Engine_CastAlu",      (0.560, 0.565, 0.572), 1.00, 0.520, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "engine_alu_worn":("MAT_Engine_CastAlu_Worn", (0.430, 0.428, 0.424), 1.00, 0.660, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "engine_blk":     ("MAT_Engine_BlockIron",    (0.180, 0.176, 0.172), 1.00, 0.640, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "engine_plastic": ("MAT_Engine_Cover_ABS",    (0.100, 0.102, 0.108), 0.00, 0.380, 0.30, 0.05, 0.0, 0.0, None, 0.0),
    "belt_rubber":    ("MAT_Belt_Ribbed_Rubber",  (0.055, 0.052, 0.055), 0.00, 0.720, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "insulation":     ("MAT_Thermal_Insulation",  (0.720, 0.690, 0.600), 0.00, 0.900, 0.00, 0.00, 0.0, 0.40, None, 0.0),
    "filter_paper":   ("MAT_Filter_Element",      (0.680, 0.620, 0.420), 0.00, 0.920, 0.00, 0.00, 0.0, 0.30, None, 0.0),

    # ---- fluids / service ----------------------------------------------
    "fluid_oil":      ("MAT_Fluid_EngineOil",     (0.320, 0.220, 0.060), 0.00, 0.070, 0.00, 0.00, 0.85, 0.0, None, 0.0),
    "fluid_coolant":  ("MAT_Fluid_Coolant_Green", (0.180, 0.620, 0.240), 0.00, 0.060, 0.00, 0.00, 0.90, 0.0, None, 0.0),
    "fluid_washer":   ("MAT_Fluid_Washer_Blue",   (0.130, 0.320, 0.760), 0.00, 0.060, 0.00, 0.00, 0.90, 0.0, None, 0.0),
    "fluid_brake":    ("MAT_Fluid_Brake_DOT3",    (0.760, 0.680, 0.500), 0.00, 0.070, 0.00, 0.00, 0.85, 0.0, None, 0.0),
    "fluid_fuel":     ("MAT_Fuel_Tank_Surface",   (0.130, 0.135, 0.140), 0.35, 0.450, 0.00, 0.00, 0.0, 0.0, None, 0.0),

    # ---- electrical -----------------------------------------------------
    "wire_blk":       ("MAT_Wire_Loom_Black",     (0.040, 0.040, 0.042), 0.00, 0.520, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "wire_red":       ("MAT_Wire_Power_Red",      (0.480, 0.055, 0.045), 0.00, 0.520, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "wire_grn":       ("MAT_Wire_Signal_Green",   (0.090, 0.380, 0.130), 0.00, 0.520, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "wire_ylw":       ("MAT_Wire_Signal_Yellow",  (0.700, 0.600, 0.090), 0.00, 0.520, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "connector":      ("MAT_Connector_PA66",      (0.230, 0.240, 0.250), 0.00, 0.400, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "battery_case":   ("MAT_Battery_Case_PP",     (0.115, 0.118, 0.125), 0.00, 0.420, 0.10, 0.06, 0.0, 0.0, None, 0.0),

    # ---- brakes / chassis ----------------------------------------------
    "caliper":        ("MAT_Brake_Caliper_Cast",  (0.260, 0.150, 0.090), 1.00, 0.600, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "brake_pad":      ("MAT_Brake_Pad_Friction",  (0.140, 0.130, 0.125), 0.00, 0.850, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "spring_steel":   ("MAT_Suspension_Spring",   (0.115, 0.100, 0.098), 1.00, 0.520, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "shock_body":     ("MAT_Shock_Absorber_Body", (0.400, 0.405, 0.412), 1.00, 0.300, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "shock_rod":      ("MAT_Shock_Piston_Rod",    (0.820, 0.825, 0.830), 1.00, 0.080, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "bushing":        ("MAT_Suspension_Bushing",  (0.060, 0.058, 0.062), 0.00, 0.700, 0.00, 0.00, 0.0, 0.10, None, 0.0),
    "underbody":      ("MAT_Underseal",           (0.110, 0.105, 0.100), 0.00, 0.780, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "grease":         ("MAT_Grease_Film",         (0.150, 0.120, 0.070), 0.00, 0.180, 0.00, 0.00, 0.0, 0.0, None, 0.0),

    # ---- labels / misc --------------------------------------------------
    "label_white":    ("MAT_Decal_White",         (0.820, 0.820, 0.800), 0.00, 0.520, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "label_black":    ("MAT_Decal_Black",         (0.030, 0.030, 0.030), 0.00, 0.480, 0.00, 0.00, 0.0, 0.0, None, 0.0),
    "gauge_face":     ("MAT_Gauge_Face",          (0.880, 0.880, 0.870), 0.00, 0.400, 0.10, 0.05, 0.0, 0.0, None, 0.0),
    "gauge_needle":   ("MAT_Gauge_Needle_Red",    (0.700, 0.090, 0.070), 0.00, 0.350, 0.20, 0.05, 0.0, 0.0, None, 0.0),
    "foam":           ("MAT_Seat_Foam_PU",        (0.320, 0.300, 0.270), 0.00, 0.900, 0.00, 0.00, 0.0, 0.30, None, 0.0),
    "paint_red":      ("MAT_Paint_Red_Accent",    (0.520, 0.040, 0.035), 0.60, 0.300, 1.00, 0.030, 0.0, 0.0, None, 0.0),
}


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def build_materials(with_flakes=True):
    """Create (or fetch) every material and return {key: bpy.types.Material}."""
    out = {}
    for key, s in MATERIALS.items():
        (bname, rgb, metal, rough, coat, coat_r, trans, sheen,
         emis, emis_s) = s
        mat = bpy.data.materials.get(bname)
        if mat is None:
            mat = bpy.data.materials.new(bname)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out_node = nt.nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (420, 0)
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (60, 0)
        nt.links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

        lin = [_srgb_to_linear(c) for c in rgb]
        bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1.0)
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.52 if trans > 0.5 else 1.45
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = trans
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = coat
            bsdf.inputs["Coat Roughness"].default_value = coat_r
        if "Sheen Weight" in bsdf.inputs:
            bsdf.inputs["Sheen Weight"].default_value = sheen
        if emis is not None:
            el = [_srgb_to_linear(c) for c in emis]
            bsdf.inputs["Emission Color"].default_value = (el[0], el[1], el[2], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emis_s

        # metallic-flake break-up on the clearcoat (render only; glTF unaffected)
        if with_flakes and key.startswith("paint") and coat > 0.5:
            tex = nt.nodes.new("ShaderNodeTexNoise")
            tex.location = (-420, -260)
            tex.inputs["Scale"].default_value = 260.0
            tex.inputs["Detail"].default_value = 3.0
            tex.inputs["Roughness"].default_value = 0.65
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.location = (-200, -260)
            ramp.color_ramp.elements[0].position = 0.42
            ramp.color_ramp.elements[0].color = (0.008, 0.008, 0.008, 1.0)
            ramp.color_ramp.elements[1].position = 0.62
            ramp.color_ramp.elements[1].color = (0.045, 0.045, 0.045, 1.0)
            nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
            if "Coat Roughness" in bsdf.inputs:
                nt.links.new(ramp.outputs["Color"], bsdf.inputs["Coat Roughness"])

        # glass needs an alpha-blended surface method for EEVEE
        if trans > 0.5:
            try:
                mat.surface_render_method = "BLENDED"
            except Exception:
                pass
            try:
                mat.blend_method = "BLEND"
            except Exception:
                pass
            mat.use_backface_culling = False
        if key.startswith("lamp_") and key != "lamp_bulb":
            try:
                mat.surface_render_method = "DITHERED"
            except Exception:
                pass

        mat["asmb_key"] = key
        out[key] = mat
    return out


def assign(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
