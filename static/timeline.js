'use strict';

const add_delete_button = (expDiv, item) => {
    // if logged in, add a delete button
    if(item.classList.contains('logged-in')){
        const delete_button = document.createElement('a');
        delete_button.text='Delete';
        delete_button.setAttribute('class', 'btn btn-outline-danger');
        delete_button.setAttribute('role','button');
        expDiv.appendChild(delete_button);
        // expDiv.insertAdjacentHTML('afterend',
        // '<a role="button" class="btn btn-outline-danger">Delete</a>');
    }
};

function expandItem(evt){
    const item = evt.target;
    
    // if details were already loaded before, no need to load again!
    if(item.children.length !== 0) return; 
    
    const expDiv = document.createElement('div');
    expDiv.classList.add('accordion-body');

    // check if edit or experiment
    if(item.classList.contains('edit')){
        // console.log('this is an edit!')
        // console.log(`/api/edit/${item.id}`)
        
        // fetch edit details from server
        fetch(`/api/edit/${item.id}`)
            .then((response) => response.json())
            .then((edit_data) => {
                const {curr, prev} = edit_data;
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
                add_delete_button(expDiv, item);
                item.appendChild(expDiv);
            });
    }
    
    if(item.classList.contains('experiment')){
        // console.log('this is an experiment!')
        // console.log(`/api/experiment/${item.id}`)

        // fetch experiment details from server
        fetch(`/api/experiment/${item.id}`)
            .then((response) => response.json())
            .then((exp_data) => {
                // insert experiment data in new div
                expDiv.classList.add('newline'); // formatting issues
                expDiv.insertAdjacentHTML('beforeend', `<h3>${exp_data['commit_msg']}</h3>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>(${exp_data['commit_date']})</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${exp_data['notes']}</p>`)
                // item.appendChild(expDiv);
                // console.log(item);
                add_delete_button(expDiv, item);
                item.appendChild(expDiv);
            });
    }
    
    // particularly the first edit, which is the first version of the recipe on creation
    if(item.classList.contains('createEdit')){
        fetch(`/api/edit/${item.id}`)
            .then((response) => response.json())
            .then((edit_data) => {
                const {curr} = edit_data;
                const expDiv = document.createElement('div');
                expDiv.classList.add('newline');
                expDiv.insertAdjacentHTML('beforeend', `<h3>${curr['title']}</h3>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${curr['description']}</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${curr['ingredients']}</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${curr['instructions']}</p>`)
                add_delete_button(expDiv, item);
                item.appendChild(expDiv);
                
            });
    };
    
}

const timelineItems = document.querySelectorAll('.timeline-item-details');
for(const timelineItem of timelineItems){
    timelineItem.addEventListener('show.bs.collapse', expandItem)
}