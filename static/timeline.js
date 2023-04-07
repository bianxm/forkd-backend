'use strict';

function expandItem(evt){
    const item = evt.target;
    item.disabled = true;

    // check if edit or experiment
    if(item.classList.contains('edit')){
        // console.log('this is an edit!')
        // console.log(`/api/edit/${item.id}`)
        
        // fetch edit details from server
        fetch(`/api/edit/${item.id}`)
            .then((response) => response.json())
            .then((edit_data) => {
                const {curr, prev} = edit_data;
                const expDiv = document.createElement('div');
                // for each of title, desc, ingredients, instructions
                for(const attr of ['title', 'description','ingredients','instructions']){
                    // check if it changed. if yes:
                    if(curr[attr] !== prev[attr]){
                        // get the unified diff via jsdiff
                        const this_diff = Diff.createPatch(attr,prev[attr], curr[attr]);
                        // get the diff2html object and add to the div to be inserted
                        const this_diff2Html = Diff2Html.html(this_diff, {
                            matching: 'lines',
                            drawFileList: false,
                            srcPrefix: false,
                            dstPrefix: false,
                            outputFormal: 'line-by-line'
                        });
                        expDiv.insertAdjacentHTML('beforeend', `<div>${this_diff2Html}</div>`)
                    }
                }
                // and then insert div 
                item.insertAdjacentElement('afterend', expDiv);
            });
    }
    
    if(item.classList.contains('experiment')){
        // console.log('this is an experiment!')
        // console.log(`/api/experiment/${item.id}`)

        // fetch experiment details from server
        fetch(`/api/experiment/${item.id}`)
            .then((response) => response.json())
            .then((exp_data) => {
                // console.log(exp_data);
                // insert experiment data in new div
                const expDiv = document.createElement('div');
                expDiv.insertAdjacentHTML('beforeend', `<h3>${exp_data['commit_msg']}</h3>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>(${exp_data['commit_date']})</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${exp_data['notes']}</p>`)
                item.insertAdjacentElement('afterend', expDiv);
            });
    }
    
    // particularly the first edit, which is the first version of the recipe on creation
    if(item.classList.contains('createEdit')){
        fetch(`/api/edit/${item.id}`)
            .then((response) => response.json())
            .then((edit_data) => {
                const {curr} = edit_data;
                const expDiv = document.createElement('div');
                expDiv.insertAdjacentHTML('beforeend', `<h3>${curr['title']}</h3>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${curr['description']}</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${curr['ingredients']}</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${curr['instructions']}</p>`)
                item.insertAdjacentElement('afterend', expDiv);
            });
    };
}

const timelineItems = document.querySelectorAll('.timeline-item');
for(const timelineItem of timelineItems){
    timelineItem.addEventListener('click', expandItem)
}