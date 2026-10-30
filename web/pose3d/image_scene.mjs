// SPDX-License-Identifier: GPL-3.0-only
import {rigMannequin} from './mhr.mjs';

// A one-person image opens in its source camera. In a group scene, replace
// only the selected person's pose without moving the rest of the composition.
export function applyImagePose(scene,number,result){
    const next=structuredClone(scene),person=next.people.find(p=>p.id===number);
    if(!person)throw Error('The selected person was removed. Import again.');
    if(next.people.length===1){
        const imported=structuredClone(result.scene);
        imported.people[0].id=number;
        imported.mask_mode=next.mask_mode;imported.outline=next.outline;
        return imported;
    }
    person.joints=structuredClone(result.pose.joints);
    person.source_frame=structuredClone(result.pose.source_frame);
    person.position[1]-=Math.min(...rigMannequin(person).vertices.map(v=>v[1]));
    return next;
}
