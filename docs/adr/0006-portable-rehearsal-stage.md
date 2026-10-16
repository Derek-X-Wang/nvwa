---
status: proposed
---

# Save the rehearsal stage with the Work

People and offline agents need to exchange the same character presentation. Save validated lighting, background, floor, camera framing and requested quality as typed stage settings in Work schema2, changed through the same atomic `SetStage` command as Studio. Schema2 requires stage settings; the exact schema1 shape is accepted and upgraded to a default white stage without changing the character, animation or revision. A save writes schema2, so receiving applications must support the new format. Keeping version1 while silently adding fields would obscure the compatibility boundary because earlier readers reject unknown fields.

Store camera distance and target height in character-relative units so ordinary character scaling retains useful framing. Projection conversion must produce finite values or report unsupported extreme rendering scale; it must not silently rewrite the character. Stage sliders and Studio orbit preview during a gesture and commit one history step, with Escape restoring the prior state. Player orbit is temporary. Quality is an explicit portable request whose actual rendered effects and cost are verified separately on each target. Bevy entities and GPU handles remain outside the document. Studio and Player fit the saved camera into the scene area left by their actual controls; window layout and DPI do not edit the Work. The same computed projection drives rendering and picking. High requests a 4096 key-light shadow map and 4× MSAA. Experimental screen-space contact shadows remain disabled because the actual same-pose Web comparison produced visible skin speckle.

Room import, collision, physics, a running-Studio bridge and multiplayer are later boundaries. Historical captures remain bound to their archived source; they cannot establish that a changed renderer was run. Current compilation, runtime use, visual evidence and performance measurements remain separate acceptance gates.
