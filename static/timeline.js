'use strict';

function expandItem(evt){
    const item = evt.target;

    // check if edit or experiment
    if(item.classList.contains('edit')){
        console.log('this is an edit!')
        // only need to display the fields that were edited....
        // choices:
        //   * check differences between current edit and previous edit on python side
        //   * check differences between current edit and previous edit on js side
        //   * have a flag of which rows were edited? separate table? same table?   
    }
    
    if(item.classList.contains('experiment')){
        console.log('this is an experiment!')
        console.log(`/api/experiment/${item.id}`)
        // fetch commit_msg and notes from server
        fetch(`/api/experiment/${item.id}`)
            .then((response) => response.json())
            .then((exp_data) => {
                console.log(exp_data);
                const expDiv = document.createElement('div');
                expDiv.insertAdjacentHTML('beforeend', `<h3>${exp_data['commit_msg']}</h3>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>(${exp_data['commit_date']})</p>`)
                expDiv.insertAdjacentHTML('beforeend', `<p>${exp_data['notes']}</p>`)
                item.insertAdjacentElement('afterend', expDiv);
            });
    }
}

const timelineItems = document.querySelectorAll('.timeline-item');
for(const timelineItem of timelineItems){
    timelineItem.addEventListener('click', expandItem)
}

// const addExperimentLink = document.querySelector('#add-experiment');
// addExperimentLink.addEventListener('click', ()=>{
//     console.log('add an experiment!');
//     const addExperimentForm = document.createElement('form');
//     addExperimentForm.classList.add(''); 
//     document.querySelector('#form-holder').appendChild(addExperimentForm);
// });