SELECT * FROM full_team WHERE id=6133;

SELECT * FROM round1, full_team WHERE round1.id = full_team.round1_id AND full_team.id=6133;

SELECT * FROM base_team;

SELECT id FROM full_team;
