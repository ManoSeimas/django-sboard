function(doc) {
    if(doc.parents) {
        var parent_id = doc.parents[doc.parents.length - 1];
        emit(parent_id, 1);
    }
}
