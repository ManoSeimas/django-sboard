function(keys, values, rereduce) {
    var max_val = '000000';
    values.forEach(function(value) {
        if (value.length === 6 && value > max_val) {
            max_val = value;
        }
    });

    return max_val;
}
